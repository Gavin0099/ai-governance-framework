# DBL First Slice Reviewer Reconstruction Kit

> 更新日期：2026-03-31
> 相關文件：`docs/dbl-first-slice-validation-plan.md`

---

## 目的

這份 kit 用來支援 Step 2 的 reviewer reconstruction test。

它的用途是檢查：

- reviewer 是否能只靠 first-slice DBL surface 重建缺失原因
- reviewer 是否能區分 limitation proof 與 capability claim
- reviewer 是否能指出 current slice 的不足，而不是只接受 formal presence

---

## Reviewer 任務

reviewer 應回答以下問題：

1. first-slice DBL gate 顯式表達了哪些 missing-state？
2. 這些 missing-state 為什麼足以改變 decision posture？
3. gate 是如何避免把缺失包裝成 pass 的？
4. insufficiency-like example 為什麼是 limitation proof，而不是 capability proof？

---

## Reviewer 不應依賴的東西

reviewer 不應依賴：

- 作者額外口頭補充
- prompt history
- 未寫入 artifact 的直覺假設

如果 reviewer 只能靠這些外部補充完成判讀，代表 surface 還不夠成熟。

---

## 判讀重點

reviewer 應特別留意：

- explicit signal presence 不等於 semantic sufficiency
- insufficiency-like example 不應被當成 adequacy judgment
- first slice 是否只是 framing-only，還是真正 runtime-related

---

## 交付內容

reviewer 至少應留下：

- reconstruction summary
- failure / limitation 判讀
- 目前 slice 的不足點
- 是否建議進下一階段 validation

---

## 一句話

這份 reconstruction kit 的目標，是確認 first-slice DBL 已經能讓 reviewer 只靠 artifact 形成有約束力的判讀，而不是只看見一個漂亮 framing example。
