# Entry-Layer Contract：workflow artifact 最小閉環契約

## 目的

這份文件定義最小 contract，讓 workflow skills 產生的 artifact 能被 runtime 辨識，而不是停留在脫離治理系統的 UX layer。

它不是要把 repo 變成完整 workflow engine，而是先定義一個最小閉環：

`tech-spec -> precommit -> create-pr`

## 為什麼需要這份 contract

目前 repo 已經有：

- runtime governance hooks
- reviewer handoff 與 trust surfaces
- 導向 workflow 的 skills
- CI 與 repo boundary validation

但還缺一個明確 contract 去回答：

- workflow skill 到底產出什麼
- runtime 允許辨識什麼
- 各 workflow step 之間是什麼關係
- 某一步缺失時，現階段屬於哪種 consequence class

如果沒有這份 contract，workflow skill 只會增加入口數量，不會增加系統理解力。

## 範圍

這份 spec 定義：

- entry layer 的最小 object model
- 第一個 closed loop 的 edge semantics
- 三種 workflow artifact 的最低辨識條件
- 在 hard enforcement 尚未存在前，可以先使用哪些 consequence class

這份 spec **不定義**：

- generic DAG engine
- multi-agent orchestration
- AI 是否真的沒跳過內部推理的自動證明
- 每個 task 都必須完整走過 workflow
- 以 workflow evidence 取代 domain/runtime evidence

## 必須保留的邊界

這個 repo 主要仍是：

- runtime governance system
- evidence / reviewer-surface system

entry layer 是上游協調層，未來可以供 runtime 辨識，但它不是另一套治理 authority。

## 最小閉環

### `tech_spec`

角色：

- 把非 trivial 的意圖轉成有範圍、可審查的計畫

### `validation_evidence`

角色：

- 在 reviewer handoff 之前，留下本地驗證證據

### `pr_handoff`

角色：

- 把範圍、風險、與證據打包成 reviewer 可讀的 handoff

目標不是證明所有 workflow path，而是讓**至少一條有意義的 path**明確、可辨識、且邊界清楚。

## Workflow Object Model

runtime 不應相信單純的聊天宣稱。  
最小可辨識單位必須是**可驗證的 workflow artifact**，不是 skill 名稱，也不是口頭描述。

### Object Types

1. **Workflow Artifact**  
   某個 workflow step 產生，供後續辨識的檔案或結構化紀錄

2. **Workflow Recognition Result**  
   runtime 端對 artifact 是否存在、是否有效、是否適用於目前 scope 的解讀

3. **Workflow Consequence Class**  
   在 hard enforcement 尚未存在前，missing / invalid recognition 應該落在哪一類後果

## Artifact Envelope

所有 entry-layer artifact 最少都應包含：

- `artifact_type`
- `skill`
- `scope`
- `timestamp`
- `status`
- `provenance`

## Artifact Storage Convention

建議路徑：

`artifacts/workflow-entry/<task-slug>/<artifact_type>.json`

例如：

- `artifacts/workflow-entry/add-runtime-loop/tech_spec.json`
- `artifacts/workflow-entry/add-runtime-loop/validation_evidence.json`
- `artifacts/workflow-entry/add-runtime-loop/pr_handoff.json`

這個 convention 本身不是 verdict，只是讓 runtime-side observer 能用穩定位置辨識 artifact。

## 必要欄位語義

### `artifact_type`

標識 artifact 類型，例如：

- `tech_spec`
- `validation_evidence`
- `pr_handoff`

### `skill`

標識是哪個 workflow skill 產生，例如：

- `tech-spec`
- `precommit`
- `create-pr`

### `scope`

把 artifact 綁定到可辨識的工作範圍。最少應包含：

- `task_text` 或等價的 task identifier
- 相關 repo root
- changed surface hint（檔案、diff 範圍、或 PR scope）

如果 scope 無法和目前工作對應，runtime 不應視為 applicable。

### `timestamp`

記錄 artifact 產生時間，供未來 freshness / ordering 規則使用。

### `status`

記錄該 step 的結果類型。最小允許值：

- `completed`
- `passed`
- `failed`
- `partial`

### `provenance`

記錄 artifact 是如何產生的，至少應包含：

- producing tool / skill identity
- repository path context
- tool 或 framework version（若可取得）

## Edge Semantics

第一個 closed loop 的 edge 不是單純箭頭，而要說清楚關係型別。

### `sequencing`

表示某一步通常發生在另一步之前。  
這是順序建議，不是 prerequisite 證明。

### `prerequisite`

表示後續步驟若缺少前一步 artifact，就不應被視為 fully valid。

### `coverage`

表示某一步的結果，能覆蓋後續步驟的某種 trust / completeness 面向。

### `recommendation`

表示該步驟在特定條件下建議出現，但不是 minimum closed loop 的一部分。

## 最小閉環的 edge 定義

### `tech_spec -> validation_evidence`

edge types：

- `sequencing`
- `coverage`

意義：

- 非 trivial work 通常應先有 `tech_spec`
- spec 能幫助後續 validation evidence 的解讀

### `validation_evidence -> pr_handoff`

edge types：

- `prerequisite`
- `coverage`

意義：

- 沒有本地 validation evidence 的 `create-pr` 不應被視為 fully trusted
- `precommit` 產生的 evidence 能覆蓋 reviewer handoff 的本地驗證面向

## Recognition Rules

artifact 只有在以下條件都成立時，才算 recognized：

- envelope 結構有效
- scope 可對應到目前工作上下文
- provenance 存在
- status 對該 artifact 類型有意義

「檔案存在」本身不夠。

## Observation States

在 policy 介入之前，workflow artifact 應先被描述成純 observation 語言：

- `recognized`
- `missing`
- `incomplete`
- `stale`
- `unverifiable`

這些狀態只表示 observation 結果，不表示：

- AI 一定做了某步
- AI 一定跳過某步
- task 已 workflow-compliant
- task 已 workflow-non-compliant

## Consequence Classes

### `informational`

只記錄狀態，暫時沒有 trust 影響。

### `advisory_degradation`

缺少 recognition 會降低 workflow guidance 品質，但不直接降低 runtime trust。

### `confidence_reduction`

缺少 recognition 會降低 handoff / process 完整性的可信度。

### `escalation_candidate`

缺少 recognition 可能值得引發人工 review 或額外 scrutiny。

### `verdict_prerequisite`

未來相容欄位：某步若缺，後續不能被視為 fully valid。  
但目前 minimum contract 尚未啟用這個 class。

## Initial Consequence Mapping

### Missing `tech_spec`

預設 class：

- `advisory_degradation`

### Missing / failed `validation_evidence` before `create-pr`

預設 class：

- `confidence_reduction`

可進一步視情況升到：

- `escalation_candidate`

### Missing `pr_handoff`

預設 class：

- `informational`

## 最小可運作範例

```yaml
entry_layer_contract:
  artifact_envelope:
    required_fields:
      - artifact_type
      - skill
      - scope
      - timestamp
      - status
      - provenance

  artifacts:
    tech_spec:
      produced_by: tech-spec
      required_payload:
        - task
        - problem
        - scope
        - non_goals
        - evidence_plan

    validation_evidence:
      produced_by: precommit
      required_payload:
        - entrypoint
        - mode
        - result
        - summary

    pr_handoff:
      produced_by: create-pr
      required_payload:
        - change_summary
        - scope_included
        - scope_excluded
        - risk_summary
        - evidence_summary

  edges:
    - from: tech_spec
      to: validation_evidence
      semantics: [sequencing, coverage]

    - from: validation_evidence
      to: pr_handoff
      semantics: [prerequisite, coverage]

  consequence_defaults:
    missing_tech_spec: advisory_degradation
    missing_validation_before_pr: confidence_reduction
    missing_pr_handoff: informational
```

## 下一步建議

不要先加更多 workflow skills。  
比較合理的順序是：

1. 先讓 `tech-spec`、`precommit`、`create-pr` 對齊這份 artifact contract
2. 定義 artifact 應落在哪裡、命名怎麼固定
3. 只為 minimum envelope 加上 runtime-side recognition logic
4. 在 recognition 穩定前，保持 consequence class 為 advisory
