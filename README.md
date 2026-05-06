# 🚀 AI Governance Framework

讓 AI 任務變得 **可追蹤、可審核、可交接** 的治理框架。

## 🔍 這個 Repo 解決什麼問題？
當 AI / Agent 幫你執行任務時，常見問題：

- 不知道 AI 實際做了哪些步驟
- 不知道輸出是否有足夠證據支撐
- reviewer 之間缺少一致判斷基準
- 任務交接時容易遺失背景與限制
- 多 repo 導入 AI 後缺乏一致治理標準

👉 這個框架解決的不是「AI 會不會錯」  
👉 而是：

**當 AI 完成任務後，我們是否有足夠證據讓人類做判斷？**

## 💡 一句話說明
這是一個位於「AI 執行」與「人類決策」之間的治理層（governance layer），
負責產生可供審核的證據與狀態。

## 🧠 核心定位

👉 本框架 **不做決策**  
👉 它提供 **讓人做決策的材料**

## ⚙️ 核心流程（完整治理流程）

```mermaid
flowchart TD
  %% 風格定義
  classDef init fill:#E3F2FD,stroke:#1976D2,stroke-width:2px;
  classDef gate fill:#FFEBEE,stroke:#D32F2F,stroke-width:2px;
  classDef agent fill:#FFF4E5,stroke:#FF9800,stroke-width:2px;
  classDef output fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px;
  classDef decision fill:#FFFDE7,stroke:#FBC02D,stroke-width:2px;
  classDef state fill:#E8F5E9,stroke:#388E3C,stroke-width:2px;

  %% 主流程：完全線性，避免 Mermaid layout 被 loop 拉歪
  Start((開始<br/>Start)) --> Init[<b>會話初始化<br/>Session Initialization</b><br/>載入狀態 / 記憶 / 契約<br/>Load state / memory / contract]
  Init --> Planning[<b>任務規劃<br/>Task Planning</b><br/>Agent plans under governance context]
  Planning --> PRE

  subgraph PreGate[前置治理<br/>Pre-task Gate]
    direction TB
    PRE[pre_task_check.py] --> Check1{計畫 / 假設 / 前提驗證<br/>Plan / Assumption / Precondition}
    Check1 --> PreDecision{前置決策<br/>Pre-task Decision}
  end

  PreDecision -->|允許 Allow| Exec[<b>任務執行<br/>Task Execution</b><br/>Agent execution boundary]
  PreDecision -->|限制 Restrict| Exec
  PreDecision -->|升級 Escalate| Reviewer
  PreDecision -->|中止 Stop| FinalVerdict

  Exec --> POST

  subgraph PostGate[後置治理<br/>Post-task Gate]
    direction TB
    POST[post_task_check.py] --> Check2{契約 / 證據 / 策略驗證<br/>Contract / Evidence / Policy}
    Check2 --> FinalVerdict{最終裁定<br/>Final Verdict}
  end

  FinalVerdict --> Closeout[<b>會話收斂<br/>Session Closeout</b><br/>Snapshot / Trace / Verdict / Index]

  Closeout --> Reviewer

  subgraph Reviewer[審查與信任<br/>Review & Trust]
    direction TB
    R[審查者<br/>Reviewer] --> T[信任訊號<br/>Trust Signal] --> A[發布產出<br/>Publication Artifacts]
  end

  %% Feedback 不接回 Init，避免破壞主幹 layout
  Closeout -.-> FeedbackNote[<b>回饋下一輪</b><br/>Feedback to next session<br/>memory / state / closeout]

  %% 樣式
  class Init,Closeout init;
  class PRE,Check1,POST,Check2 gate;
  class Planning,Exec agent;
  class R,T,A,Reviewer output;
  class PreDecision,FinalVerdict decision;
  class FeedbackNote state;
```

```mermaid
flowchart TD

  classDef start fill:#E3F2FD,stroke:#1976D2,stroke-width:2px,color:#000;
  classDef pre fill:#FFF3E0,stroke:#F57C00,stroke-width:2px,color:#000;
  classDef agent fill:#ECEFF1,stroke:#607D8B,stroke-width:2px,color:#000;
  classDef post fill:#FFEBEE,stroke:#D32F2F,stroke-width:2px,color:#000;
  classDef closeout fill:#E8F5E9,stroke:#388E3C,stroke-width:2px,color:#000;
  classDef review fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#000;
  classDef decision fill:#FFFDE7,stroke:#FBC02D,stroke-width:2px,color:#000;
  classDef note fill:#FAFAFA,stroke:#9E9E9E,stroke-width:1px,stroke-dasharray:5 5,color:#000;

  Start(("開始<br/>Start"))

  Start --> S1["1. 會話初始化<br/>Session Start<br/>session_start.py"]
  S1 --> S1A["產生狀態快照<br/>Derived State Snapshot"]
  S1 --> S1B["版本相容性檢查<br/>Version Compatibility"]
  S1 --> S1C["權限表載入與過濾<br/>Authority Table Loading"]
  S1 --> S1D["規則包與契約載入<br/>Rule Pack / Contract Loading"]
  S1 --> S1E["任務等級偵測<br/>Task Level Detection"]
  S1 --> S1F["讀取前次收斂脈絡<br/>Closeout Context"]
  S1A --> S1G["建立會話治理上下文<br/>Session Governance Context"]
  S1B --> S1G
  S1C --> S1G
  S1D --> S1G
  S1E --> S1G
  S1F --> S1G

  S1G --> P0["2. 前置治理檢查<br/>Pre Task Check<br/>pre_task_check.py"]
  P0 --> P1["計畫新鮮度檢查<br/>Plan Freshness"]
  P0 --> P2["架構影響預覽<br/>Architecture Impact"]
  P0 --> P3["執行期契約解析<br/>Runtime Contract Resolve"]
  P0 --> P4["規則分類<br/>Rule Classification"]
  P0 --> P5["假設與邊界檢查<br/>Assumption / Boundary Check"]
  P0 --> P6["證據完整性閘門<br/>Evidence Integrity Gate"]
  P0 --> P7["前提條件閘門<br/>Precondition Gate"]
  P0 --> P8["執行期注入觀察<br/>Runtime Injection Observation"]

  P1 --> D1{"前置決策<br/>Pre-task Decision"}
  P2 --> D1
  P3 --> D1
  P4 --> D1
  P5 --> D1
  P6 --> D1
  P7 --> D1
  P8 --> D1

  D1 --> A0["3. Agent 執行邊界<br/>Agent Execution Boundary"]
  D1 --> RV["停止或升級審查<br/>Stop / Escalate"]

  A0 --> A1["AI Agent 執行任務<br/>Execute Task"]
  A1 --> A2["輸出結果<br/>Code / Docs / Artifacts / Claims"]

  A2 --> Q0["4. 後置治理檢查<br/>Post Task Check<br/>post_task_check.py"]
  Q0 --> Q1["治理契約驗證<br/>Governance Contract Validator"]
  Q0 --> Q2["修改意圖與假設檢查<br/>Intent / Assumption Check"]
  Q0 --> Q3["公開 API 差異檢查<br/>Public API Diff"]
  Q0 --> Q4["領域驗證器<br/>Domain Validators"]
  Q0 --> Q5["驅動與執行證據<br/>Driver / Runtime Evidence"]
  Q0 --> Q6["失敗完整性檢查<br/>Failure Completeness"]
  Q0 --> Q7["政策衝突檢查<br/>Policy Conflict Check"]
  Q0 --> Q8["必要證據分類<br/>Required Evidence Classification"]

  Q1 --> D2{"後置決策<br/>Post-task Decision"}
  Q2 --> D2
  Q3 --> D2
  Q4 --> D2
  Q5 --> D2
  Q6 --> D2
  Q7 --> D2
  Q8 --> D2

  D2 --> RV2{"執行期裁定<br/>Runtime Verdict"}
  RV --> RV2

  RV2 --> E0["5. 會話收斂與 Artifact 產生<br/>Session End<br/>session_end.py"]
  E0 --> E1["候選收斂紀錄<br/>Candidate Closeout"]
  E0 --> E2["標準化收斂紀錄<br/>Canonical Closeout"]
  E0 --> E3["裁定 Artifact<br/>Verdict Artifact"]
  E0 --> E4["追蹤 Artifact<br/>Trace Artifact"]
  E0 --> E5["執行階段摘要<br/>Runtime Phase Summary"]
  E0 --> E6["會話索引<br/>Session Index NDJSON"]
  E0 --> E7["每日記憶與提升訊號<br/>Daily Memory / Promotion Signals"]
  E0 --> E8["重新產生治理狀態檔<br/>Regenerate .governance-state.yaml"]

  E1 --> B0["可審查資料包<br/>Artifact Bundle"]
  E2 --> B0
  E3 --> B0
  E4 --> B0
  E5 --> B0
  E6 --> B0
  E7 --> B0
  E8 --> B0

  E8 --> N1[".governance-state.yaml<br/>衍生上下文快照<br/>Derived Context Snapshot<br/>非權威來源 / Not Authority"]

  B0 --> R0["6. 審查與發布面<br/>Reviewer / Publication"]
  R0 --> R1["審查者交接<br/>Reviewer Handoff"]
  R0 --> R2["發布面總覽<br/>Release Surface Overview<br/>release_surface_overview.py"]
  R2 --> R3["發布就緒狀態<br/>Release Readiness"]
  R2 --> R4["資料包清單<br/>Bundle Manifest"]
  R2 --> R5["發布清單<br/>Publication Manifest"]
  R2 --> R6["升級權限表面<br/>Escalation Authority Surface"]
  R2 --> R7["信任與審查訊號<br/>Trust / Review Signals"]

  class Start,S1,S1A,S1B,S1C,S1D,S1E,S1F,S1G start;
  class P0,P1,P2,P3,P4,P5,P6,P7,P8 pre;
  class A0,A1,A2 agent;
  class Q0,Q1,Q2,Q3,Q4,Q5,Q6,Q7,Q8 post;
  class D1,D2,RV,RV2 decision;
  class E0,E1,E2,E3,E4,E5,E6,E7,E8,B0 closeout;
  class R0,R1,R2,R3,R4,R5,R6,R7 review;
  class N1 note;
```

## 📦 你會得到什麼輸出？

```json
{
  "decision_usage_allowed": false,
  "analysis_safe_for_decision": false,
  "token_observability_level": "step_level",
  "token_source_summary": "mixed(provider, estimated)",
  "provenance_warning": "mixed_sources"
}
```

解讀：
- `decision_usage_allowed = false`  
  → 禁止自動決策使用
- `analysis_safe_for_decision = false`  
  → 證據不足以支持決策
- `token_*`  
  → 觀測用途（debug / visibility），不是品質

## ⚠️ Misuse Boundary（不可誤用）

本框架為 `non-authoritative`（非權威）設計。

❌ 不可用於：

- 自動封鎖（gating）
- 評分 / 排序（scoring / ranking）
- production decision logic
- 自動判定成功 / 失敗

👉 `Evidence ≠ Decision`

## 🧩 架構分層

治理執行以 Session Gate（pre/post）為核心，Token 與 Trust 相關輸出皆為 non-authoritative reviewer context，不可直接進入自動決策。

## 🧪 最小使用流程

安裝：

```bash
pip install -r requirements.txt
```

quickstart：

```bash
python governance_tools/quickstart_smoke.py \
  --project-root . \
  --plan PLAN.md \
  --contract examples/usb-hub-contract/contract.yaml \
  --format human
```

👉 會：

- 模擬治理流程
- 執行 hooks
- 產生 evidence
- 輸出 reviewer surface

檢查治理狀態：

```bash
python governance_tools/governance_drift_checker.py --repo . --framework-root .
```

## 📈 Adoption Path

### 🔧 導入到其他 Repo

```bash
python governance_tools/adopt_governance.py --target /path/to/repo
```

## 📁 核心目錄

- Runtime Hooks  
  `session_start / pre_task_check / post_task_check / session_end`
- Governance Tools  
  `adoption / drift / readiness`
- Governance  
  `contracts / rules / architecture`
- Reviewer Surface  
  `status / trust / handoff`

## 🧪 Experimental（實驗性）

Cross-repo token slice：

- 僅用於 observability
- 非 production 保證
- 非 decision-safe

## ❌ 這個 Repo 不是

- 決策引擎
- 測試替代品
- correctness proof
- orchestration system

