# Reviewer Signal Split

> 狀態：active
> 建立：2026-03-31
> 適用：Beta Gate condition 2 與之後的 reviewer run

---

## 為什麼需要這份文件

如果 reviewer onboarding failure 只被記成單一 pass/fail，資訊會太粗。

同樣一個 failed run，背後可能是完全不同的問題：

- reviewer 找不到入口
- reviewer 找到對的檔案，但看錯用途
- reviewer 讀了文件，卻重建錯 runtime boundary
- reviewer 理解表面內容，但判錯 escalation / judgment

如果不把這些 signal 分開，最後很容易修錯地方。

---

## 四個診斷層

### 1. Discoverability failure

reviewer 不知道從哪裡開始，或不知道下一步去哪裡找。

常見徵象：

- 停在 repo root 沒方向
- 錯過 `README.md`、`start_session.md`、或相關 reviewer pack
- 找不到 drift checker 或 adoption path

通常代表：

- entry path 問題
- navigation 問題
- README / root pointer 問題

---

### 2. Interpretation failure

reviewer 找到對的檔案，但誤解它在說什麼。

常見徵象：

- 把 framework 當成純文件集合
- 把 framework governance 與 consuming-repo governance 混在一起
- 把 rule pack、runtime hook、domain contract 混成同一層

通常代表：

- naming 問題
- framing 問題
- heading / first-sentence 問題

---

### 3. Decision reconstruction failure

reviewer 讀了 DBL 或 runtime 相關材料，但重建出錯的 system boundary。

常見徵象：

- 把 limitation example 看成 capability example
- 在只有 explicit presence check 的地方，腦補成 semantic sufficiency
- 用 reviewer 自己的直覺偷偷升級 runtime 能力

通常代表：

- DBL framing 問題
- artifact contract 問題
- example / reviewer-pack mismatch

---

### 4. Escalation judgment failure

reviewer 其實看懂 surface，但對結果套了錯的 judgment。

常見徵象：

- 把 reconstruction failure 當成 runtime bug
- 把 onboarding blockage 當成 DBL limitation
- 明明只是 wording 問題，卻提議擴 runtime authority

通常代表：

- authority / decision-model communication 問題
- reviewer guidance 問題

---

## 記錄規則

每次 reviewer run fail 時，在提修法前，都要先把**第一個有意義的 failure** 分到這四層之一。

如果同時有多層問題：

- 先記最早出現的那一層

不要從 failed run 直接跳到 framework 變更，而沒有先記錄失敗屬於哪一層。

---

## 作者的工作規則

當 reviewer run fail 時：

- 先修最低層 failure
- 不要把 discoverability failure 當成 DBL 問題
- 不要把 wording 問題當成 runtime 問題
- 不要把 runtime boundary limitation 當成單純 onboarding 問題

這份文件的存在，就是為了把這些 distinction 固定住。
