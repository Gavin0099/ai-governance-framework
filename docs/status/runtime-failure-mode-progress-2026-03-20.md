# Runtime Failure-Mode Progress — 2026-03-20

## 摘要

到這個時間點，repo 已經擁有第一個 execution-layer failure-mode slice。

它還不是完整的 fault-injection harness，  
但也不再只是 control-plane 上的口頭主張。

當時 runtime 已可 machine-readably 處理 5 類具體 failure mode：

- `missing_required_evidence`
- `invalid_evidence_schema`
- `policy_conflict`
- `illegal_override`
- `runtime_failure`

另外也已有第一個最小 replay check，用來觀察 determinism。

---

## 什麼已經變成真實能力

### 1. Failure-mode contract

repo 已有明確的 failure-mode 測試契約，例如：

- `docs/failure-mode-test-plan.md`
- `governance/failure_mode_test_matrix.v0.1.json`
- `tests/test_failure_mode_test_matrix.py`

這表示 failure handling 已開始有 machine-readable break-test scope，而不是只留在未來待辦。

### 2. Runtime handling

這些 failure mode 不再只是文件分類，而是真正進入 runtime decision path。

也就是說：

- runtime 會辨識這些 failure 類型
- artifact 會留下相對應訊號
- reviewer 不必完全靠人工猜測 failure 類別

### 3. Minimal replay

當時也已有第一個最小 replay check，用來驗證：

- 類似輸入是否導向一致結果
- runtime verdict 是否過度依賴偶發環境狀態

---

## 還沒做到的事

在這個時點，系統仍然不是：

- full runtime fault-injection harness
- 完整 failure-mode taxonomy coverage
- machine-authoritative recovery planner

所以這份 progress 應被理解成：

> 第一個 runtime failure-mode slice 已落地，
> 但離完整 fault-injection 或大規模 automated recovery 仍有距離。

---

## 這份 progress 的意義

這個里程碑的重要性不在於 failure mode 數量本身，而在於：

- failure-mode handling 從文件主張變成 runtime reality
- reviewer 可以從 artifact 看到具體類型
- failure handling 開始具有可重建性

這替後續更細緻的 failure-mode governance 打下了真正可執行的基礎。

---

## 一句話結論

到 2026-03-20 為止，repo 已經擁有第一個真實的 runtime failure-mode slice：它還不完整，但已不再只是 control-plane 上的承諾，而是能進 decision path、留下 artifact、供 reviewer 重建的實際能力。
