# 治理分級提案：minimal / standard / strict（Governance Tiering）

> 依據：framework main [`f8868c81`](https://github.com/Gavin0099/ai-governance-framework/tree/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5)（2026-10-27 10:06 台北時間）；fleet 唯讀量測於 2026-10-27（台北時間）。全程唯讀，沒有寫入任何 consumer repo。
> 標記：**[已查證]** = 實測數字或 code 已讀；**[推估]** = 推論，尚未量測。
> **合併本文件 ≠ 核准實作。** 下方每一步都要 owner 另外確認後才能動手（沿用 [2026-10-improvement-plans.md](2026-10-improvement-plans.md) 的慣例）。

---

## 1. 問題：治理重量跟 repo 風險倒過來（risk inversion）

把框架導入其他 repo 後，觀察到「過度治理」的感受。量測結果顯示這不只是感受，而是結構性的：

- **高風險的 firmware fork**（`fwupd`、`zephyr`）治理檔只佔 **0–2%**，60 天內只有 1 個只改治理的 commit。**[已查證]**
- **低風險的遊戲、App、個人專案**治理檔佔 **50–85%**，commit 了數十到數百 MB 的 evidence（截圖、影片、HTML），25–78% 的 commit 改到 `memory/` 或 `artifacts/`。**[已查證]**
- **每次 session 的指令 context 幾乎都一樣**（AGENTS.md 13–30 KB，再加 copilot-instructions 12.5 KB、CLAUDE.md/GEMINI.md 各 5.5 KB），**跟風險無關**。其中 50–85% 是一段只有在「更新框架」時才用得到的程序（見 §4 #2）。**[已查證]**

**推估的原因**：治理量取決於「AI 在這個 repo 跑了多少 session」，而不是「這個 repo 有多危險」。新開的個人專案從第一天就由 agent 依框架完整產出 closeout、evidence 和 memory；fork 進來的大型 firmware repo 只留了框架殼。**[推估]**

## 2. 方法與抽樣

| 項目 | 內容 |
|---|---|
| Public repo | 15 個，本機 blobless clone。git 歷史時間窗為 2026-08-28 到 2026-10-27（60 天），用 `GIT_NO_LAZY_FETCH=1` 避免卡住 |
| Private repo | 5 個，用 GitHub API 讀檔案樹和最近 100 個 commit。**本文只放匿名化後的彙總數字**（見 §2.1） |
| 不納入 | 從 6/7 月就沒更新、而且 shallow fetch 失敗的 repo（`Ashfall`、`Hearth`、`ZoneTruth` 等）；還沒導入的 repo（`KidsCharacterKit`、`ulani-epaper`、`wordtreegarden-site`、`sprout-space`、`FinancialAdvisorGPT`） |
| 「治理檔」的定義 | 路徑符合以下其一：`governance/`、`memory/`、`artifacts/`、`AGENTS*.md`、`CLAUDE.md`/`GEMINI.md`、`contract.yaml`、`PLAN.md`、`.governance*`、`.claude/`、`.codex/`、`.agents/`、`.github/hooks/`、`copilot-instructions*`、治理用 workflow、submodule、`validators/` |
| 已知偏差 | `.codex/`、`.agents/` 可能放了產品自己的 skill，所以治理檔佔比可能偏高。「改到的檔案中治理佔比」= 窗內每個 commit 改到的檔案裡，治理檔所佔比例的平均 |
| CI | 只抽 4 個 repo 最近 ≤100 次 workflow run，計算各 workflow 的次數、失敗數和 wall time，**不是**完整的帳單分鐘數 |

### 2.1 匿名化規則

本 repo 是 public。私有 repo 一律以「私有 repo A–D」稱呼，只放類型和彙總數字，不放名稱、URL 或技術棧。第 5 個私有 repo 治理佔比只有 3%，只計入總數。

## 3. 量測結果

### 3.1 Public repo [已查證]

| Repo | 類型 / 風險 | 檔案數 | 治理檔佔比 | 60 天 commit / 只改治理的 | 改到的檔案中治理佔比 | AGENTS.md | 其中 Update Intent Rule | 備註 |
|---|---|---|---|---|---|---|---|---|
| [fwupd](https://github.com/Gavin0099/fwupd) | firmware fork / 高 | 4882 | **2%** | 122 / 1 | – | 26.8 KB | 16.1 KB（60%） | memory 75 KB |
| [zephyr](https://github.com/Gavin0099/zephyr) | firmware fork / 高 | 64901 | **0%** | – | – | – | – | – |
| [TacticalGo](https://github.com/Gavin0099/TacticalGo) | Swift 遊戲 / 低 | 2526 | **51%** | 107 / 18 | 45% | 30.1 KB | 16.1 KB（53%） | 治理資料 173 / 395 MB；435 張 png、75 支 mp4；155 個 closeout 類檔案 |
| [wasteland-chronicles](https://github.com/Gavin0099/wasteland-chronicles) | GDScript 遊戲 / 低 | 2121 | **52%** | 258 / **85** | 43% | 19.9 KB | 16.1 KB（81%） | 治理資料 176 / 570 MB；PLAN.md 125 KB |
| [life-crossroads](https://github.com/Gavin0099/life-crossroads) | Swift App / 低 | 390 | **80%** | 32 / 10 | 67% | 28.0 KB | 16.1 KB（57%） | 治理資料 39.7 / 45.5 MB |
| [DiceMercenaries](https://github.com/Gavin0099/DiceMercenaries) | 遊戲 / 低 | 200 | **72%** | 13 / 5 | – | 24.2 KB | 16.1 KB（66%） | `memory/` 2.58 MB，其中單一 evidence JSON 666 KB |
| [ai-assisted-ssdlc-docs](https://github.com/Gavin0099/ai-assisted-ssdlc-docs) | 文件 / 低 | 424 | 66% | 108 / 39 | 62% | 23.9 KB | 16.1 KB（67%） | – |
| [crystal-bracelet-studio](https://github.com/Gavin0099/crystal-bracelet-studio) | web / 低 | 108 | 66% | 26 / 8 | – | 18.8 KB | 16.1 KB（85%） | – |
| [usb-logic-trace-correlator](https://github.com/Gavin0099/usb-logic-trace-correlator) | HW 工具 / 中 | 109 | **84%** | 9 / 3 | – | 13.2 KB | 0 | – |
| [lecroy-vse-toolkit](https://github.com/Gavin0099/lecroy-vse-toolkit) | HW 工具 / 中 | 357 | 60% | 23 / 0 | 69% | 21.4 KB | 16.1 KB（75%） | – |
| [uvm-agent-lab](https://github.com/Gavin0099/uvm-agent-lab) | 驗證實驗 / 中 | 482 | 33% | 87 / 5 | 10% | 28.5 KB | 14.4 KB（50%） | – |
| [usb-if-hub-spec-reference](https://github.com/Gavin0099/usb-if-hub-spec-reference) | spec 參考 / 中 | 873 | 11% | – | – | 21.3 KB | 14.0 KB（66%） | – |
| [spec-reference-kit](https://github.com/Gavin0099/spec-reference-kit) | spec 參考 / 低 | 132 | 73% | 0 / 0 | – | 19.7 KB | 14.4 KB（73%） | – |
| [BeatLab](https://github.com/Gavin0099/BeatLab) | iOS / 低 | 255 | 36% | 6 / 1 | – | 22.0 KB | 16.1 KB（73%） | – |
| [campaign-forge](https://github.com/Gavin0099/campaign-forge) | 個人工具 / 低 | 306 | 25% | 17 / 3 | – | 13.0 KB | 0 | – |

### 3.2 私有 repo（匿名彙總）[已查證]

| 標籤 | 類型 | 彙總數字 |
|---|---|---|
| 私有 repo A | 正式上線 web | 以下為 A–D 合計：治理檔佔比 21–68%；commit 進 git 的 evidence 合計約 **650 MB**；`memory/` 最大 0.9 MB，單一 review log 最大約 200 KB；PLAN.md 最大 **325 KB**；非 merge commit 中改到 `memory/` 或 `artifacts/` 的比例為 25–78%；**2 個 repo 的 AGENTS.md 超過 32 KiB**（34–40 KB） |
| 私有 repo B | 資料蒐集工具 | （同上，不分列） |
| 私有 repo C | 學習 App | （同上，不分列） |
| 私有 repo D | 個人工具 | （同上，不分列） |

### 3.3 摩擦訊號 [已查證]

| 訊號 | 數字 |
|---|---|
| 治理 CI 失敗率（最近 ≤100 次 run） | 私有 repo 兩個治理 workflow 約 37%；另一個私有 repo 約 33%；TacticalGo 的 `Governance Drift` 為 2/16 |
| 治理 CI 時間 | 每次 drift 約 1 分鐘。**CI 分鐘數不是主要成本** |
| 專門抱怨治理負擔的 issue 或 commit | 很少（uvm-agent-lab 4 個 commit、ai-assisted-ssdlc-docs 1 個）。痛點主要表現為 commit 被治理檔稀釋，而不是有人明確抱怨 |
| 文件／紀錄類 commit 訊息比例 | life-crossroads 47%、ai-assisted-ssdlc-docs 38%、DiceMercenaries 38%、TacticalGo 27%、wasteland-chronicles 27%；fwupd 1% |
| 框架本身已察覺的跡象 | `governance/copilot-instructions-template.md` 已經加了「DONE Boundary：不要自動接續 artifact 鏈（triage → decision → contract → gate → acceptance → freeze）」，可見之前就發現過頭了，只是打了補丁 |

## 4. 成本機制排名（成本 vs 對低風險 repo 的價值）

| # | 機制 | 成本 | 價值（低風險 repo） | 標記 |
|---|---|---|---|---|
| 1 | **evidence（png、mp4、html、大 JSON）直接 commit 進 `artifacts/` 和 `memory/`** | repo 膨脹數十到數百 MB，而且永久留在歷史中；clone、CI checkout、agent 搜尋都會變慢 | 低。review 完之後幾乎不會再看 | 已查證 |
| 2 | **每份 AGENTS.md 都帶完整的 `AI Governance Update Intent Rule`** | 12/14 個 public repo 都有，每份 14–16 KB（佔 50–85%），每次 session 都會載入 | 幾乎為零。只在「更新 AI Governance」時才用得到 | 已查證 |
| 3 | **Codex 截斷** | 見 §5。AGENTS.md 超過 32 KiB 時，尾端會被直接截掉、不會警告 | 負值。被截掉的正是 repo 自己的禁止行為和 Contract 規則 | 上限已查證；被截掉的是哪幾節為推估 |
| 4 | **memory 只會增加、不會清** | 單一 review log 可達約 200 KB；`memory/` 最大 2.6 MB（DiceMercenaries） | 中。但 `memory_janitor` 只看 hot memory（active_task） | 已查證 |
| 5 | **每次 session 都強制 closeout，加上必填的 Governance Contract 區塊（`LOADED` 一定要有 `SYSTEM_PROMPT`）** | 每次多讀 `SYSTEM_PROMPT.md` 17.7 KB + `AGENT.md` 11.8 KB，加上固定輸出；Contract Output 段落本身也有 5–7.8 KB | 低風險 repo 價值很低 | 規則已查證；token 數為推估 |
| 6 | **整包複製 `governance/*.md` 和全部規則包** | 每個 repo 37 個 md（約 385 KB）+ 20 個規則檔；Swift 遊戲 repo 也會拿到 `kernel-driver` 規則 | 很低 | 已查證 |
| 7 | **多 agent hook 全部裝**（Claude、Codex、Copilot 加 git pre-commit/pre-push） | 多了會壞的地方；ownership、closeout 相關 bug 集中在這裡（#256、#257、#249、#233） | 中 | 已查證 |
| 8 | **`governance-drift` CI** | 每次約 1 分鐘 | 中：抓漂移有用 | 已查證 |

## 5. Codex 的 32 KiB AGENTS.md 上限

- Codex 的 `project_doc_max_bytes` 預設為 **32 × 1024 bytes**，而且是整條 root→cwd 路徑上所有 AGENTS.md **合計**的額度。超過時，最後一個檔會被截到剩餘額度，之後的檔直接跳過；只寫進 log，TUI 不會顯示。**[已查證]**
  - 原始碼 `DEFAULT_PROJECT_DOC_MAX_BYTES`：https://github.com/openai/codex/blob/main/codex-rs/config/src/config_toml.rs
  - 截斷邏輯：https://github.com/openai/codex/blob/main/codex-rs/core/src/agents_md.rs
  - Issue「silently truncated」：https://github.com/openai/codex/issues/7138
  - 文件說法不一致（per-file 還是 cumulative）：https://github.com/openai/codex/issues/36371
- 本次樣本中有 2 個私有 repo 的 AGENTS.md 為 34–40 KB，已經超過上限。public repo 最大是 30.1 KB（TacticalGo），還剩 2.6 KB 餘裕，再加一節就會超過。**[已查證]**
- 框架慣例是把 repo 自己的規則（Forbidden Behaviors、Contract Output）放在檔尾，所以**最先被截掉的正是 repo 自己的規則**。**[推估]**
- 暫時的緩解：在 `~/.codex/config.toml` 設 `project_doc_max_bytes = 65536`。這只能治標，context 還是一樣大。

## 6. 框架根因（permalink 固定在 `f8868c81`）[已查證]

| # | 根因 | 位置 |
|---|---|---|
| R1 | **沒有 profile、tier 或 minimal 開關。** CLI 只有 `--target`、`--framework-root`、`--refresh`、`--dry-run`、`--check-env` | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/governance_tools/adopt_governance.py#L1164-L1176 |
| R2 | **不分 repo 類型，整包複製 `governance/*.md`**（排除 PLAN.md，共 37 檔、約 385 KB） | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/governance_tools/adopt_governance.py#L205-L227 |
| R3 | **複製全部規則包**（avalonia、cpp、csharp、gdscript、kernel-driver、swift 等 20 檔） | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/governance_tools/adopt_governance.py#L230-L252 |
| R3' | 其實已經有按 repo 類型挑規則包的函式（`_detect_repo_type`、`_get_default_rule_packs`），只是 R3 沒有用 | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/governance_tools/adopt_governance.py#L609-L659 |
| R4 | **payload layering 的 `always_load` 包含整份 `PLAN.md`，沒有大小上限** | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/governance_tools/adopt_governance.py#L662-L680 |
| R4' | 連 L0 任務的 `always_load` 也是 `SYSTEM_PROMPT.md` + `AGENT.md` + `PLAN.md` | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/governance_tools/task_level_detector.py#L103-L120 |
| R5 | **所謂「最小」baseline 其實一點都不小。** `baselines/repo-min/AGENTS.md` 有 19.4 KB，其中 L21–L351（約 16 KB）就是 Update Intent Rule | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/baselines/repo-min/AGENTS.md#L21-L351 |
| R6 | **刻意 commit memory 和 evidence**：gitignore hygiene 只排除 runtime、session、`*.db`，註解寫明「Committed memory/ and evidence files are intentionally kept.」；沒有大小或保留期限 | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/governance_tools/adopt_governance.py#L718-L741 |
| R7 | **每次 session 都有 closeout 義務** | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/AGENTS.base.md#L91-L110 |
| R8 | **memory 壓力檢查只看 hot memory**，review log、evidence 會一直增加 | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/governance_tools/memory_janitor.py#L74-L98 |
| R9 | **hook 安裝無法挑選 agent**：`install-hooks.sh` 只有 `--target`、`--dry-run`、`--no-verify`、`--repository-id` | https://github.com/Gavin0099/ai-governance-framework/blob/f8868c8173c1ee9c8ea466513d8f7b25ddb2d8a5/scripts/install-hooks.sh#L30-L52 |

**現有的開關（都只管單一任務，不管整個 repo）**

- 任務層級的 `L0/L1/L2`，以及 SYSTEM_PROMPT §3.4 的「L0 Fast-Track」。
- copilot 範本裡的 DONE Boundary Rules。
- `onboard-external-repo.sh --no-smoke --no-hook-verify`。
- B-4 的 L0–L4 是「**量測**導入深度」，不是「**選擇**導入深度」，而且還沒實作（[2026-10-improvement-plans.md §B-4](2026-10-improvement-plans.md#b-4-fleet-7-訊號看不出深度--導入深度-l0l4)）。

## 7. 提案：三個 profile

| 機制 | `minimal` | `standard` | `strict` |
|---|---|---|---|
| AGENTS.md（base + repo 規則）的大小上限 | **≤ 8 KB** | ≤ 16 KB | ≤ 24 KB；**任何 profile 都不能 ≥ 32 KiB** |
| Update Intent Rule | 從 AGENTS.md 移出，改放 `governance/UPDATE_PROCEDURE.md`，AGENTS.md 只留 3 行指標 | 同左 | 同左 |
| `governance/*.md` | `SYSTEM_PROMPT` 精簡版 + `AGENT.md` | 依 repo 類型挑選 | 全部 |
| 規則包 | 用 `_get_default_rule_packs` 挑 | 同左 | 同左，加 domain 規則 |
| `PLAN.md` 進 context 的方式 | 只載入 `plan_summary.py` 產生的摘要（≤ 8 KB） | 同左 | 摘要；需要時才讀全文 |
| `memory/` | 只留 active_task 和決策；單檔 ≤ 30 KB，舊的輪替到 archive | 單檔 ≤ 50 KB，總量 ≤ 300 KB | 完整，但要輪替 |
| `artifacts/` evidence | **不 commit**（加進 gitignore）；只 commit 摘要和 hash | 放 CI artifacts 或 LFS，設保留期限；git 裡只放摘要和 hash | git 裡放摘要和 hash；原始檔依 domain 要求另外保存 |
| session closeout 和 Contract Output 區塊 | 選用：只在 L2 或 owner 要求時才做 | L1 以上 | 每次 |
| agent hook | 不裝，只跑 drift CI | 只裝實際使用的 agent | 全部 |
| `governance-drift` CI | 有，並加 context-budget 檢查 | 有 | 有，加 contract、domain validator |
| 對應 B-4 的深度（觀測用） | 目標 L2 | 目標 L3 | 目標 L4 |

**設計原則**
- profile 決定「**裝什麼、載入多少**」；任務層級 `L0/L1/L2` 決定「**這次任務要多嚴**」。兩者正交，不合併。
- profile 寫在 `.governance/baseline.yaml`，讓 `--refresh` 能沿用，drift checker 也能讀取。
- strict 不是 standard 的「加量版」，差別主要在 domain contract、validator 和 hook 是否完整。**evidence 進 git 的規則在三個 profile 一致：只放摘要和 hash。**

### 7.1 各 repo 建議等級 [推估，需 owner 確認]

| 等級 | Repo |
|---|---|
| `strict` | [fwupd](https://github.com/Gavin0099/fwupd)、[zephyr](https://github.com/Gavin0099/zephyr)，以及未來的 kernel-driver / firmware repo（這兩個 repo 目前已經很輕，升 strict 主要是讓規則明確，不是加檔案） |
| `standard` | 私有 repo A（正式上線 web）、私有 repo B（資料蒐集工具）、[uvm-agent-lab](https://github.com/Gavin0099/uvm-agent-lab)、[lecroy-vse-toolkit](https://github.com/Gavin0099/lecroy-vse-toolkit)、[usb-logic-trace-correlator](https://github.com/Gavin0099/usb-logic-trace-correlator)、[usb-if-hub-spec-reference](https://github.com/Gavin0099/usb-if-hub-spec-reference) |
| `minimal` | [TacticalGo](https://github.com/Gavin0099/TacticalGo)、[wasteland-chronicles](https://github.com/Gavin0099/wasteland-chronicles)、[life-crossroads](https://github.com/Gavin0099/life-crossroads)、[DiceMercenaries](https://github.com/Gavin0099/DiceMercenaries)、[BeatLab](https://github.com/Gavin0099/BeatLab)、[campaign-forge](https://github.com/Gavin0099/campaign-forge)、[crystal-bracelet-studio](https://github.com/Gavin0099/crystal-bracelet-studio)、[ai-assisted-ssdlc-docs](https://github.com/Gavin0099/ai-assisted-ssdlc-docs)、[spec-reference-kit](https://github.com/Gavin0099/spec-reference-kit)、私有 repo C（學習 App）、私有 repo D（個人工具） |

## 8. 實作步驟、工作量與驗收（**每一步都要 owner 另外核准**）

| 步驟 | 內容 | 工作量（粗估） | 驗收條件 |
|---|---|---|---|
| S1 | 把 Update Intent Rule 從 `baselines/repo-min/AGENTS.md` 和範本移到 `governance/UPDATE_PROCEDURE.md`（或 skill），AGENTS.md 只留 3 行指標；`external_governance_submodule_updater.py` 改成讀新位置 | 0.5 天 | `baselines/repo-min/AGENTS.md` < 4 KB；對任一 consumer `--refresh` 後 AGENTS.md 少 ≥ 14 KB；「把 AI Governance 更新到最新」這類請求的路由測試照常通過 |
| S2 | `adopt_governance.py --profile minimal\|standard\|strict` 加上 profile manifest（裝哪些 docs、規則包、hook、workflow），R3 改用 `_get_default_rule_packs`，profile 寫進 `.governance/baseline.yaml` | 2–3 天 | 三個 profile 各一個 fixture 測試；`minimal` 安裝後治理檔 ≤ 15 個；Swift fixture 不含 `kernel-driver` 規則；沒給 `--profile` 時行為和現在相同（向下相容） |
| S3 | evidence 和 memory 預算：依 profile 產生 gitignore（`artifacts/evidence/**` 等）；drift 檢查 `memory/` 單檔和總量上限；`memory_janitor` 擴充到 review log 輪替 | 1 天 | `minimal` fixture 放入 1 MB 的 png 時 `git status` 看不到；超過預算時 drift 依 profile 給 warning 或 fail；**不碰歷史中既有的檔案** |
| S4 | context budget：drift 檢查 AGENTS.md（加上 CLAUDE.md、copilot-instructions）在各 profile 上限內，**≥ 32 KiB 一律 fail**；`always_load` 的 `PLAN.md` 改成 `plan_summary.py` 的輸出，並加上限 | 1 天 | 一個 33 KiB 的 AGENTS.md fixture → fail，訊息指向 Codex 上限；`PLAN.md` 300 KB 的 fixture 在 session start 實際載入 ≤ 8 KB |
| S5 | closeout 和 Contract Output 依 profile 決定是否強制：修改 `AGENTS.base.md` 和範本的措辭，`session_end` 在 `minimal` 時不把 `closeout_missing` 判成 fail-closed（與 ADR-0002 / [#258](https://github.com/Gavin0099/ai-governance-framework/pull/258)「envelope 是 identity，不是 closeout 義務」對齊） | 0.5–1 天 | `minimal` fixture 在沒有 closeout 時 verdict 不是 fail；`strict` 行為完全不變；既有 closeout 測試全部通過 |
| S6 | fleet rollout：逐一 `--refresh --profile <tier>` 並用 PR 檢查（一個 repo 一個 PR） | 約 1 天（約 18 個 repo） | 每個 repo 的 AGENTS.md 在 budget 內；drift 綠燈；B-4 實作後的深度與 §7 的目標一致 |
| | **合計** | **約 6–7.5 人天** | |

建議順序：**S1 → S4 → S2 → S3 → S5 → S6**。S1 半天就能做完，又能立即解決 Codex 截斷；S4 防止以後再長回來。

## 9. 非目標（Non-goals）

- **不改寫歷史，不 force push。** 已經 commit 的數百 MB evidence 會留著；本提案只停止繼續累積。要真正縮小 repo，必須用 `git filter-repo` 加 force push，違反現行原則，不在範圍內。
- 不降低 `strict` 的任何既有保證，也不改 firmware/driver domain contract。
- 不合併任務層級 `L0/L1/L2` 和 repo profile。
- 不取代 B-4（B-4 是觀測，本提案是選擇；兩者互補）。
- 不新增 blocking gate；S3 和 S4 的預算檢查預設是 warning，只有「≥ 32 KiB」會 fail（理由：超過就會被 Codex 默默截斷）。

## 10. 待 owner 決定

1. **三個 profile 的上限數字**（8 / 16 / 24 KB；memory 30 / 50 KB）要不要調整？
2. **`minimal` 是否完全不裝 agent hook？** 還是保留 Claude 的 SessionStart 讀回，但不強制 closeout？
3. **evidence 放哪裡：** Actions artifacts（有保留期限，免費額度內）還是 Git LFS（有容量配額）？`standard` 要用哪一種？
4. **沒給 `--profile` 時的預設值：** 維持現狀（向下相容）還是改成 `standard`？
5. **§7.1 的分級**，特別是私有 repo A、B 和 HW 工具類 repo，要放 standard 還是 strict？
6. **S5 要不要等 #233 / #256 / #258 的 closeout ownership 定案後再做？**（建議要等，避免兩邊同時改 `session_end`）

## 11. 相關 issue / proposal

| 連結 | 關聯 |
|---|---|
| [2026-10-improvement-plans.md §B-4 導入深度 L0–L4](2026-10-improvement-plans.md#b-4-fleet-7-訊號看不出深度--導入深度-l0l4) | B-4 用來觀測導入深度，本提案用來選擇導入深度；§7 最後一列是兩者的對應關係。B-4 驗收用的 repo 清單與本文 §7.1 部分重疊 |
| [2026-10-improvement-plans.md 計畫 3：Repo 瘦身 + 文件分層](2026-10-improvement-plans.md#計畫-3repo-瘦身--文件分層) | 框架本身的 `artifacts/` 和 `memory/` 膨脹，就是本文 R6 在框架 repo 上的表現 |
| [#233](https://github.com/Gavin0099/ai-governance-framework/issues/233) | 正式結案命令和 closeout 路徑；S5 要等它的設計定案 |
| [#247](https://github.com/Gavin0099/ai-governance-framework/issues/247) | Claim Ceiling 測試來源。它的「自動加註、不新增 gate」做法與本文「預設 warning、不新增 blocking gate」一致 |
| [#249](https://github.com/Gavin0099/ai-governance-framework/issues/249) | closeout 用 mtime 比對造成誤判：強制 closeout 的維護成本 |
| [#256](https://github.com/Gavin0099/ai-governance-framework/issues/256)、[#257](https://github.com/Gavin0099/ai-governance-framework/issues/257) | Claude ownership deadlock、Save progress 指令跑不起來：多 agent hook 全裝的成本（§4 #7） |
| [#258](https://github.com/Gavin0099/ai-governance-framework/pull/258) | ADR-0002「session envelope 是 identity，不是 closeout 義務」，是 S5 的前提 |

## 12. 查證狀態總表

| 主張 | 狀態 |
|---|---|
| §3 各表的檔案數、佔比、commit 數、AGENTS.md 和段落大小 | 已查證（本機 git 和 GitHub API，2026-10-27） |
| Codex 32 KiB 合計上限、靜默截斷 | 已查證（上游原始碼和 issue） |
| 被截掉的是 repo 自己的規則 | 推估（依段落順序推論，沒有實際跑 Codex 驗證） |
| R1–R9 | 已查證（`f8868c81` 原始碼） |
| 每次 session 的 token 成本 | 推估（由 bytes 換算，沒有用 tokenizer 量測） |
| 「治理量跟著 session 數走」的成因 | 推估 |
| CI 成本很小 | 部分查證（4 個 repo、≤100 次 run 的 wall time；沒有拉帳單） |
| §7.1 分級、§8 工作量 | 推估，需 owner 確認 |

---

> **再次聲明：合併本文件只代表「問題與方向的紀錄」被接受，不代表核准 §8 任何一步的實作。**
