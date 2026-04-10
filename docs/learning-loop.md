# Learning Loop

> Version: 1.0
> Related: `docs/falsifiability-layer.md`, `docs/misinterpretation-log.md`

---

## 目的

`Learning Loop` 用來定義 framework 如何把真實失敗轉成可追蹤、可回應、可收斂的學習流程。

這一層不把 failure 當成單純事件紀錄，而是要求每一個被觀測到的失敗都要留下可判讀的 outcome，避免系統只累積 log，卻沒有形成可重用經驗。

這裡關心的不是「有沒有做出反應」而已，而是：

- failure 是否被正式記錄
- 反應是否落到明確 outcome
- repeated failure 是否會提高後續審查強度

---

## 核心原則

### 1. 每個 observed failure 都要有 documented outcome

一個 failure 被記錄後，不能停在「知道有問題」。
至少要落到下列四種 outcome 之一：

| Outcome | Meaning | Required documentation |
|---------|---------|------------------------|
| `model_adjusted` | 調整 decision threshold、routing 或 runtime mechanism | 說明調整內容與理由 |
| `doc_updated` | 更新文件、規則或 reviewer guidance | 說明更新位置與欲修正的誤解 |
| `no_change_justified` | 決定先不調整，但有清楚理由 | 說明為何 failure 不構成足夠變更依據 |
| `investigation_pending` | 已確認需要追查，但尚未完成定論 | 記錄待查問題、觀察窗口與後續責任 |

`investigation_pending` 不是沉默或拖延的替代詞。
如果 observation window 結束後仍沒有 outcome，就代表 learning loop 沒有真正關閉。

### 2. learning response 不是只有改 code

可接受的學習回應包括：

- 調整 runtime 或 policy 機制
- 更新文件與 reviewer guidance
- 提高某類 proposal 的 evidence bar
- 把 repeated failure 放進更高審查區域

如果 failure 的真正原因是敘述不清、證據不足或 reviewer 容易誤讀，那麼 `doc_updated` 也是有效 response。

### 3. repeated failure 要提高後續 skepticism

同一類 failure 若反覆出現，系統不能每次都把它當獨立 incident。
這時 learning loop 要開始做兩件事：

1. 把該類問題推入更高 skepticism zone
2. 對同類 proposal 提高 evidence requirement

這樣 repeated failure 才會真正改變後續 decision posture，而不是只讓 log 越積越多。

---

## Outcome 的判定標準

### `model_adjusted`

使用情境：

- threshold 或 routing 要改
- runtime 機制要補強
- 原本 decision surface 的切分不夠用

需要記錄：

- 調整了哪一層
- 調整原因
- 預期降低哪種 failure

### `doc_updated`

使用情境：

- 真正問題是 wording、reviewer guidance 或規則說明不清
- failure 顯示某個邊界被反覆誤解
- 想修正的是 interpretation，不是 execution path

`doc_updated` 不能只是換句話說。
應該能指出這次更新是要減少哪種 recurring misunderstanding。

### `no_change_justified`

使用情境：

- failure 是單次 noise，不足以支撐結構調整
- 失敗原因在 implementation，而不是 governance model
- 現有機制仍可接受，只需要保留觀察

需要記錄：

- 為什麼這次 failure 不足以導致 change
- 要持續觀察哪些 signals

### `investigation_pending`

使用情境：

- 已知有 failure，但根因尚未釐清
- 需要額外 observation window 或更多 evidence
- 尚不能誠實地判成其他 outcome

需要記錄：

- 待查項目
- 預計觀察窗口
- 何時應重新判定

---

## 與 falsifiability 的關係

learning loop 不只問「要不要學」，也問「學了之後怎麼驗證」。

因此每次實質調整都應盡量連到：

- falsification condition
- observation window
- 後續是否出現 recurrence

沒有 falsification 的 learning，容易變成 narrative adjustment。
沒有 documented outcome 的 failure，則只會變成累積中的雜訊。

---

## 與 misinterpretation log 的關係

`misinterpretation-log.md` 負責記錄發生了什麼。
`learning-loop.md` 負責規定記錄之後必須產生什麼治理回應。

如果只有 observation、沒有 outcome，learning loop 就沒有真正成立。

---

## 不是什麼

`Learning Loop` 不是：

- 對每個 failure 都立刻做大改
- 用活動量假裝進步
- 只靠新增文件就宣稱系統已學會

它真正要確保的是：

> 每一個值得記住的 failure，都會被系統化地轉成可追蹤、可回顧、可再驗證的後續回應。
