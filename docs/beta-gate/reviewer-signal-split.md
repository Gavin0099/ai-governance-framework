# Reviewer Signal Split

> 狀態：active
> 建立：2026-03-31
> 適用：Beta Gate condition 2 與後續 reviewer run

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

這份文件的目的，就是把 reviewer signal 拆成可診斷的層，而不是只留下模糊的整體分數。

---

## 一句話結論

`Reviewer Signal Split` 讓 reviewer onboarding fail 不再只是單一 verdict，而能被拆成 discoverability、interpretation、reconstruction、judgment 等不同層級訊號。
