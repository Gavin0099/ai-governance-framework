# P2 Lite 多題評測結案

結案：REAL_LITE_MULTI_TASK_BENCHMARK_VALIDATED（真實 Lite 多題流程已走通）。
Skill 暫定處置：KEEP_OBSERVE / OPTIONAL（保留觀察、選用）；這是 owner 採納的評估建議，不變更 Skill packet、安裝、觸發或預設載入設定。

## 已觀察結果

| 題目 | CONTROL | Bug Fix Safety TREATMENT | 有限結論 |
|---|---|---|---|
| Easy | oracle12/12；7個NameError；品質總分無法評定 | oracle12/12；9個NameError；品質總分無法評定 | 兩者提交測試均缺少受測函式import，Skill本次未防止此缺陷；不可宣稱整體平手 |
| Medium | oracle13/13；7tests PASS；8/8 | oracle13/13；7tests PASS；8/8 | 此題評分沒有差異 |
| Hard | oracle14/14；2methods PASS；8/8 | oracle14/14；3methods PASS；8/8 | 兩者都保留真正cycle檢查；方法數不同不等於覆蓋更多或品質較高 |

三題未建立穩定的Treatment品質優勢，也不證明Skill一般無效。Earlier Real Lite單題觀察為7/8對8/8，差別在因果解釋；那是另一份既有任務/評測證據，不是四個獨立不同題目的統計樣本，不合併平均或推論一般效果。

來源：
- memory/evidence/p2-lite-parser-20260908/live/report.json：較早單題正向訊號。
- memory/evidence/three-task-real-lite-20260908/：初次CONTROL及harness失敗原始證據。
- memory/evidence/three-task-treatment-completion-20260908/：原CONTROL重收卷、fresh TREATMENT、匿名評分、freeze與unblinding及完整分項依據。
- memory/evidence/lite-harness-compatibility-20260908/review.json：已提交相容性修正審查。

## 流程與限制

三份CONTROL是首次single-run模型輸出，沒有重呼叫或補import；相容性修正後以exact原bytes重新執行host collection/oracle/regression。三份TREATMENT各只有一次fresh模型呼叫。兩臂使用相同固定task、baseline、模型、auth、timeout與環境政策；上下文路徑按執行獨立，只有TREATMENT多Skill packet。呼叫不同時發生，不是同步或重複隨機樣本。

三份fresh scorer只取得匿名材料，各題先保存並核對兩份opaque scores，才依owner授權揭盲。NameError未執行到assertions，依frozen rubric保持NOT_ASSESSABLE；oracle不能代替Regression Safety。既有freeze和report不改分、不補材料。

這是bounded JSON patch generation + host test execution，沒有模型互動工具迴圈；不能證明完整互動式Bug Fix Safety工作流的效益。評分尺度有滿分聚集，題目難度尚未校準。

Lite已觀察到：不用關ChatGPT、沒有Strict readiness/AppContainer配置、無adapter自動重試，三fixture各自完成oracle→regression evidence→匿名評分→freeze→unblind→report。既有Codex原生sandbox與runtime warnings仍存在，不宣稱完全沒有sandbox。

成本：原CONTROL模型耗時48969/39234/36203ms，fresh TREATMENT43438/39937/38766ms（Easy/Medium/Hard）。完成slice耗時199500ms，包含重收卷、3次TREATMENT與3次scorer，排除之前CONTROL與相容性修復時間；不能當成完整專案成本或平均省時證明。先前單題report.elapsed_ms=87015也是整條單題流程，不是每個模型各87秒。

## Governance成本觀察

案例為本repo三題Lite benchmark及本次durability結案；執行基準983d5fad7a4a28047b175adcddf904587a55a008。實際完整治理版本未確認；此欄不另建驗收。初輪已觀察unittest載入與AST誤拒，導致三份CONTROL完成但0/3比較完成；已修harness後保留原CONTROL再收卷。必要額外工作與既有測試/review見相容性validation.json，不重跑來填表；額外時間未量測。修正改變決策：允許忠實評估原輸出，保留Easy真實缺陷，而非歸為harness問題。若未修，可能漏掉真實回歸診斷（反事實推論）；不能證明治理淨效益。本次純提交收尾尚未觀察新的實質治理摩擦。

## Claim ceiling與下一步

NON_COUNTED / SOLO_CONTROLLED / DECISION_SUPPORT_ONLY。
不宣稱：Strict end-to-end PASS、OS scorer isolation、Formal/counted、Skill普遍有效或無效、Easy或整體benchmark品質平手、平均治理成本下降、正式通用production-ready evaluator。

P2此範圍結案；不再增加Bug Fix Safety題目。下一步候選是另選Skill的bounded評測準備，或分開的Governance Cost/Value Review（Lite vs Strict）；均須另定範圍。本次只授權scoped local commit，STOP，不push、不啟動新模型。
