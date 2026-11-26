# G4 Observer 長期觀測紀錄總覽

本目錄保存各自然產品任務（Work Item）的**去識別化**觀測報告（`report.md` 與 `evidence_index.json`），供跨任務長期追蹤與檢視。

- 僅保存去識別化摘要與雜湊引用；完整 Codex rollout JSONL、課本照片與本機敏感路徑一律保留於本機，不上傳 GitHub。
- 部分欄位若尚無可核對證據，仍會如實保存並標記為 `UNKNOWN`，不等待所有欄位補齊才歸檔。
- 本總覽僅作唯讀觀察紀錄，不作為合併 Gate、ROI 證明或跨任務排名。

| Work Item | 任務名稱 | 儲存庫 | 合併與 CI | 產品驗收 | Codex Tokens（完整度） | 人工介入 / 分鐘 | 詳細報告 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `WI-2-EXAM-ZHUYIN` | 考卷新增注音與混合考試模式 | `Gavin0099/chinese-writing-practice` | `YES` | Node 124/124 通過，Windows Chrome、WebKit 與 A4 PDF 版面驗證通過（實機 iOS Safari 待驗） | 2,783,095（`complete`） | 決策 UNKNOWN / 救援 UNKNOWN / UNKNOWN | [report.md](./WI-2-EXAM-ZHUYIN/report.md) · [json](./WI-2-EXAM-ZHUYIN/evidence_index.json) |
| `WI-3-OCR-QUALITY` | OCR 圈選詞語辨識品質改善（3 張真實課本照片 6/16 -> 16/16） | `Gavin0099/chinese-writing-practice` | `YES` | Node 132/132 通過，3 張真實課本照片（16 題）PP-OCRv5 實測 6/16 提升至 16/16（100%） | 3,548,762（`complete`） | 決策 UNKNOWN / 救援 UNKNOWN / UNKNOWN | [report.md](./WI-3-OCR-QUALITY/report.md) · [json](./WI-3-OCR-QUALITY/evidence_index.json) |
