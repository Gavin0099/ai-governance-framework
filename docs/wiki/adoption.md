# Consumer 導入

先分類 consumer 角色，再談自動化。相同檔案出現在兩個 repo，不代表兩者有相同的 evidence duty 或 update path。

## Consumer 類型

| 類型 | 可自動化上限 | 可以宣稱 | 不可以宣稱 |
|---|---|---|---|
| Submodule consumer | pointer／lock currentness | 指向 framework commit X | pointer bump 等於完整更新 |
| F-7 consumer | 受治理更新＋per-update evidence | 指定更新的 `full_update_completed` | 單一 consumer 證明 fleet rollout |
| External contract repo | contract validation | 在指定 commit 的契約符合性 | runtime governance 已導入 |
| Copy-based audit-only | provenance audit | 針對 commit X 的 copy／drift inventory | 已受支援、自動更新或 current |
| Unknown | 無 | 尚未分類 | 任何 adoption claim |

完整定義以 repo 的 [`docs/ADOPTION_MODEL.md`](https://github.com/Gavin0099/ai-governance-framework/blob/main/docs/ADOPTION_MODEL.md) 為準。

## 最小導入順序

1. 唯讀辨識 repo role 與現有 topology。
2. 定義誰是 framework source，誰是 consumer。
3. 先跑 dry-run 或 readiness diagnosis。
4. 只安裝能解決當前 failure 的最小治理面。
5. 以一個真實 vertical slice 驗證導入後路徑。
6. 記錄哪些是 installed、verified、report-only、missing。
7. 在實際使用後再決定是否擴張。

## 不要把「檔案存在」當導入成功

導入判斷至少要分開：

- framework checkout 是否存在；
- lock 是否與 checkout 一致；
- hooks 是否安裝；
- hooks 是否在目前環境實際執行；
- validator 是否被 publication path 呼叫；
- fail 時是否真的阻擋；
- final report 是否呈現 human-readable adoption summary；
- memory／receipt 是否對應實際 commit。

## 停止條件

出現以下情況時，先停在診斷或 report-only：

- consumer role 不明；
- source of truth 不明；
- repo 有無法分離的 dirty work；
- 需要修改產品檔案才能完成治理導入，但未取得授權；
- 工具只能產生報告，卻被要求宣稱 enforced；
- 為解決單一 consumer 例外，必須新增大量通用 schema 或 runtime surface；
- 導入成本已明顯高於預期返工成本。

## 成本也必須量測

導入是否值得，應看淨值：

```text
避免的缺陷／返工／交接成本
－ Agent 額外操作成本
－ reviewer 成本
－ framework 維護成本
= 實際淨價值
```

如果只量 gate 通過率、receipt 數或 session 數，會把治理活動誤當成工程成果。
